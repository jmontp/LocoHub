#!/usr/bin/env python3
"""
Create Dataset Validation Report

Generates comprehensive validation reports for locomotion datasets with automatic
documentation integration.

Features:
- Validates phase-indexed datasets against YAML configuration
- Generates minimal, focused validation reports
- Creates plots with embedded dataset name and timestamp
- Automatically updates MkDocs index for seamless documentation
- Outputs directly to documentation directory

Usage:
    # Basic validation report generation
    python create_dataset_validation_report.py --dataset converted_datasets/umich_2021_phase.parquet
    
    # With custom config directory
    python create_dataset_validation_report.py --dataset my_data.parquet --config-dir custom/config/
    
    # Without plots (faster)
    python create_dataset_validation_report.py --dataset my_data.parquet --no-plots
"""

import sys
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple

# Add parent directories to path for imports
current_dir = Path(__file__).parent
repo_root = current_dir.parent  # Go up one level from contributor_tools
sys.path.insert(0, str(repo_root))

# Import validation modules
try:
    from internal.validation_engine.dataset_validator_phase import DatasetValidator
    from internal.config_management.config_manager import ValidationConfigManager
except ImportError as e:
    print(f"❌ Error importing validation modules: {e}")
    print("Make sure you're running from the repository root directory")
    sys.exit(1)


def extract_status_from_report(report_path: Path) -> Tuple[str, str]:
    """
    Extract status and percentage from a validation report.
    
    Args:
        report_path: Path to the validation report markdown file
        
    Returns:
        Tuple of (status_emoji, status_text) e.g., ("✅", "PASSED (98.2% valid)")
    """
    try:
        with open(report_path, 'r') as f:
            content = f.read()
            
        # Look for the status line
        status_match = re.search(r'\*\*Status\*\*: (.+)', content)
        if status_match:
            status_line = status_match.group(1)
            
            # Parse the status
            if "PASSED" in status_line:
                return "✅", status_line.replace("✅", "").strip()
            elif "PARTIAL" in status_line:
                # Extract percentage
                pct_match = re.search(r'(\d+\.\d+)%', status_line)
                if pct_match:
                    return "⚠️", f"PARTIAL ({pct_match.group(1)}% valid)"
                return "⚠️", "PARTIAL"
            elif "FAILED" in status_line:
                # Extract percentage
                pct_match = re.search(r'(\d+\.\d+)%', status_line)
                if pct_match:
                    return "❌", f"FAILED ({pct_match.group(1)}% valid)"
                return "❌", "FAILED"
            else:
                return "❓", "UNKNOWN"
    except Exception:
        return "❓", "Status unavailable"
    
    return "❓", "No status found"


def update_index_file(report_name: str, dataset_name: str, mkdocs_dir: Path) -> None:
    """
    Update the index.md file to include the new validation report.
    
    Args:
        report_name: Name of the report file (e.g., "umich_2021_phase_validation_report.md")
        dataset_name: Display name for the dataset (e.g., "UMich 2021")
        mkdocs_dir: Path to the MkDocs validation reports directory
    """
    index_path = mkdocs_dir / "index.md"
    
    # Read existing index content
    if index_path.exists():
        with open(index_path, 'r') as f:
            content = f.read()
    else:
        # Create default structure if index doesn't exist
        content = """# Dataset Validation Reports

## Available Validation Reports

### Phase-Indexed Datasets
<!-- AUTO-GENERATED-REPORTS-START -->
<!-- AUTO-GENERATED-REPORTS-END -->

### Time-Indexed Datasets
<!-- AUTO-GENERATED-TIME-REPORTS-START -->
<!-- AUTO-GENERATED-TIME-REPORTS-END -->

## Understanding Validation Reports

Dataset validation reports provide:

**Summary Statistics:**
- Overall validation status (PASSED/PARTIAL/FAILED)
- Success rate percentage

**Visual Validation:**
- Plots with embedded dataset name and timestamp
- Kinematic and kinetic validation overlays
- Success rate indicators on each plot

**Minimal Report Format:**
- Focused on visual information
- Status clearly indicated
- Images contain all metadata

---

*Reports are automatically generated and integrated into documentation.*
"""
    
    # Determine if this is a phase or time dataset
    is_phase = "_phase" in report_name
    
    # Choose the appropriate markers
    if is_phase:
        start_marker = "<!-- AUTO-GENERATED-REPORTS-START -->"
        end_marker = "<!-- AUTO-GENERATED-REPORTS-END -->"
    else:
        start_marker = "<!-- AUTO-GENERATED-TIME-REPORTS-START -->"
        end_marker = "<!-- AUTO-GENERATED-TIME-REPORTS-END -->"
    
    # Find the auto-generated section
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("⚠️  Warning: Could not find auto-generation markers in index.md")
        return
    
    # Get all existing reports in the directory
    reports = {}
    for report_file in mkdocs_dir.glob("*_validation_report.md"):
        if report_file.name != "index.md":
            # Extract dataset name from filename
            name_parts = report_file.stem.replace("_validation_report", "").replace("_", " ")
            display_name = name_parts.title()
            
            # Get status from report
            status_emoji, status_text = extract_status_from_report(report_file)
            
            reports[report_file.name] = {
                'display_name': display_name,
                'status_emoji': status_emoji,
                'status_text': status_text
            }
    
    # Update with current report
    status_emoji, status_text = extract_status_from_report(mkdocs_dir / report_name)
    reports[report_name] = {
        'display_name': dataset_name,
        'status_emoji': status_emoji,
        'status_text': status_text
    }
    
    # Sort reports alphabetically by display name
    sorted_reports = sorted(reports.items(), key=lambda x: x[1]['display_name'])
    
    # Generate the reports list
    report_lines = []
    for filename, info in sorted_reports:
        # Only include reports of the same type (phase or time)
        if is_phase and "_phase" in filename:
            line = f"- **{info['display_name']}**: [{info['status_emoji']} View Report]({filename}) - {info['status_text']}"
            report_lines.append(line)
        elif not is_phase and "_time" in filename:
            line = f"- **{info['display_name']}**: [{info['status_emoji']} View Report]({filename}) - {info['status_text']}"
            report_lines.append(line)
    
    # Build the new content
    if report_lines:
        new_section = "\n".join(report_lines)
    else:
        new_section = "*(No validation reports available yet)*"
    
    # Replace the auto-generated section
    new_content = (
        content[:start_idx + len(start_marker)] +
        "\n" + new_section + "\n" +
        content[end_idx:]
    )
    
    # Write the updated index
    with open(index_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Updated index.md with {len(report_lines)} validation report(s)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate validation reports for locomotion datasets with automatic documentation integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Basic validation report:
    python create_dataset_validation_report.py --dataset converted_datasets/umich_2021_phase.parquet
    
  With custom config directory:
    python create_dataset_validation_report.py --dataset my_data.parquet --config-dir custom/config/
    
  Without plots (faster):
    python create_dataset_validation_report.py --dataset my_data.parquet --no-plots
    
  Custom output directory:
    python create_dataset_validation_report.py --dataset my_data.parquet --output custom/docs/
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--dataset", 
        required=True, 
        help="Path to phase-indexed dataset parquet file"
    )
    
    # Optional arguments
    parser.add_argument(
        "--config-dir",
        help="Directory containing validation YAML config files (default: contributor_scripts/validation_ranges/)"
    )
    
    parser.add_argument(
        "--output",
        help="Output directory for validation reports (default: docs/user_guide/docs/reference/datasets_documentation/validation_reports/)"
    )
    
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generation of validation plots (faster)"
    )
    
    parser.add_argument(
        "--no-index-update",
        action="store_true",
        help="Skip updating the index.md file"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"❌ Error: Dataset file not found: {dataset_path}")
        return 1
    
    # Extract dataset name for display
    dataset_name = dataset_path.stem.replace("_phase", "").replace("_time", "")
    dataset_display_name = dataset_name.replace("_", " ").title()
    
    print(f"🚀 Dataset Validation Report Generator")
    print(f"📂 Dataset: {dataset_path}")
    print(f"📝 Report Name: {dataset_display_name}")
    print(f"📊 Generate Plots: {'No' if args.no_plots else 'Yes'}")
    
    try:
        # Check config directory
        if args.config_dir:
            config_dir = Path(args.config_dir)
            if not config_dir.exists():
                print(f"❌ Error: Config directory not found: {config_dir}")
                return 1
            print(f"⚙️  Using custom config: {config_dir}")
        
        # Initialize validator with appropriate output directory
        print(f"\n🔍 Initializing validator...")
        validator = DatasetValidator(
            dataset_path=str(dataset_path),
            output_dir=args.output,
            generate_plots=not args.no_plots
        )
        
        # Run validation
        print(f"🔍 Running validation...")
        report_path = validator.run_validation()
        
        print(f"\n✅ Validation complete!")
        print(f"📄 Report saved: {report_path}")
        
        # Update index.md if not disabled
        if not args.no_index_update:
            report_file = Path(report_path)
            mkdocs_dir = report_file.parent
            
            print(f"\n📝 Updating documentation index...")
            update_index_file(
                report_file.name,
                dataset_display_name,
                mkdocs_dir
            )
            
            print(f"\n🎉 SUCCESS! Report created and documentation updated!")
            print(f"🌐 View in MkDocs at: /reference/datasets_documentation/validation_reports/")
        else:
            print(f"\n🎉 SUCCESS! Report created (index update skipped)")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n🛑 Report generation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)