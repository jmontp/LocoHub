#!/usr/bin/env python3
"""
Create Dataset Validation Report

Generates comprehensive validation reports for locomotion datasets and merges them
into dataset documentation for a unified view.

Features:
- Validates phase-indexed datasets against YAML configuration
- Merges validation results into dataset documentation
- Creates visually appealing validation tables and plots
- Automatically updates dataset documentation files
- Supports both merged and standalone report modes

Usage:
    # Basic validation with merge into documentation (default)
    python create_dataset_validation_report.py --dataset converted_datasets/umich_2021_phase.parquet
    
    # With custom validation ranges file
    python create_dataset_validation_report.py --dataset my_data.parquet --ranges-file custom_ranges.yaml
    
    # Generate standalone report (old behavior)
    python create_dataset_validation_report.py --dataset my_data.parquet --no-merge
"""

import sys
import argparse
import re
from pathlib import Path
from typing import Tuple, Dict

# Add parent directories to path for imports
current_dir = Path(__file__).parent
repo_root = current_dir.parent  # Go up one level from contributor_tools
sys.path.insert(0, str(repo_root))

# Import validation modules
try:
    from internal.validation_engine.report_generator import ValidationReportGenerator
except ImportError as e:
    print(f"❌ Error importing validation modules: {e}")
    print("Make sure you're running from the repository root directory")
    sys.exit(1)


def get_existing_short_codes() -> Dict[str, str]:
    """
    Extract all existing short codes from dataset documentation.
    
    Returns:
        Dictionary mapping short codes to dataset names
    """
    codes = {}
    docs_dir = Path(__file__).parent.parent / "docs" / "reference" / "datasets_documentation"
    
    if not docs_dir.exists():
        return codes
    
    for doc_file in docs_dir.glob("dataset_*.md"):
        try:
            with open(doc_file, 'r') as f:
                content = f.read()
                # Look for pattern like "Subject ID Format**: `XX##_" or "Subject ID Format**: `XX##_AB"
                match = re.search(r'Subject ID Format[^`]*`([A-Z0-9]+)_', content)
                if match:
                    code = match.group(1)
                    dataset_name = doc_file.stem.replace('dataset_', '')
                    codes[code] = dataset_name
        except Exception:
            continue
    
    return codes


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
  Basic validation with merge into documentation (default):
    python create_dataset_validation_report.py --dataset converted_datasets/umich_2021_phase.parquet
    
  With custom validation ranges file:
    python create_dataset_validation_report.py --dataset my_data.parquet --ranges-file custom_ranges.yaml
    
  Generate standalone report (old behavior):
    python create_dataset_validation_report.py --dataset my_data.parquet --no-merge
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
        "--ranges-file",
        help="Path to validation ranges YAML file (default: contributor_tools/validation_ranges/default_ranges.yaml)"
    )
    
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Generate standalone report instead of merging into dataset documentation"
    )
    
    parser.add_argument(
        "--short-code",
        help="Short code for dataset (e.g., UM21 for UMich 2021, GT23 for Georgia Tech 2023)"
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
    
    # Check for short code collisions if provided
    if args.short_code:
        existing_codes = get_existing_short_codes()
        if args.short_code in existing_codes:
            print(f"\n❌ Error: Short code '{args.short_code}' is already used by {existing_codes[args.short_code]}")
            print(f"📋 Existing short codes: {', '.join(sorted(existing_codes.keys()))}")
            return 1
        print(f"✅ Short code '{args.short_code}' is available")
    
    try:
        # Determine which validation ranges file to use
        if args.ranges_file:
            ranges_file = Path(args.ranges_file)
            if not ranges_file.exists():
                print(f"❌ Error: Validation ranges file not found: {ranges_file}")
                return 1
            print(f"⚙️  Using custom validation ranges: {ranges_file}")
        else:
            # Use default ranges file
            project_root = Path(__file__).parent.parent
            ranges_file = project_root / "contributor_tools" / "validation_ranges" / "default_ranges.yaml"
            if not ranges_file.exists():
                print(f"❌ Error: Default validation ranges file not found: {ranges_file}")
                return 1
            print(f"⚙️  Using default validation ranges: {ranges_file}")
        
        # Initialize report generator with ranges file
        print(f"\n🔍 Initializing report generator...")
        report_generator = ValidationReportGenerator(ranges_file=str(ranges_file))
        
        if args.no_merge:
            # Generate standalone validation report (old behavior)
            print(f"🔍 Running validation (standalone mode)...")
            report_path = report_generator.generate_report(str(dataset_path), generate_plots=True)
            
            print(f"\n✅ Validation complete!")
            print(f"📄 Report saved: {report_path}")
            
            # Update index.md for standalone reports
            report_file = Path(report_path)
            mkdocs_dir = report_file.parent
            
            print(f"\n📝 Updating documentation index...")
            update_index_file(
                report_file.name,
                dataset_display_name,
                mkdocs_dir
            )
            
            print(f"\n🎉 SUCCESS! Standalone report created!")
            print(f"🌐 View in MkDocs at: /reference/datasets_documentation/validation_reports/")
        else:
            # Merge validation into dataset documentation (new default behavior)
            print(f"🔍 Running validation (merge mode)...")
            doc_path = report_generator.update_dataset_documentation(
                str(dataset_path), 
                generate_plots=True,
                short_code=args.short_code
            )
            
            print(f"\n✅ Validation complete!")
            print(f"📄 Documentation updated: {doc_path}")
            
            print(f"\n🎉 SUCCESS! Dataset documentation updated with validation!")
            print(f"🌐 View in MkDocs at: /reference/datasets_documentation/")
        
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