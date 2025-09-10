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
import glob
from pathlib import Path
from typing import Tuple, Dict, List

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


def check_documentation_complete(doc_path: Path) -> Tuple[bool, List[str]]:
    """
    Check if documentation has any TODO placeholders.
    
    Args:
        doc_path: Path to documentation file
        
    Returns:
        Tuple of (is_complete, list_of_todo_lines)
    """
    if not doc_path.exists():
        return False, ["Documentation file does not exist"]
    
    todos = []
    with open(doc_path, 'r') as f:
        for i, line in enumerate(f, 1):
            if '[TODO:' in line:
                todos.append(f"Line {i}: {line.strip()}")
    
    return len(todos) == 0, todos


def update_mkdocs_navigation(dataset_name: str, doc_filename: str) -> bool:
    """
    Add dataset to mkdocs.yml navigation if not already present.
    
    Args:
        dataset_name: Display name for the dataset (e.g., "GTech 2021")
        doc_filename: Documentation filename without extension (e.g., "dataset_gtech_2021")
        
    Returns:
        True if navigation was updated, False if already exists
    """
    mkdocs_path = Path(__file__).parent.parent / "mkdocs.yml"
    
    if not mkdocs_path.exists():
        print(f"❌ Error: mkdocs.yml not found at {mkdocs_path}")
        return False
    
    with open(mkdocs_path, 'r') as f:
        lines = f.readlines()
    
    # Check if dataset already exists in navigation
    doc_ref = f"reference/datasets_documentation/{doc_filename}.md"
    for line in lines:
        if doc_ref in line:
            print(f"✅ Dataset already in navigation: {dataset_name}")
            return False
    
    # Find the Available Datasets section
    datasets_section_idx = None
    indent_level = None
    for i, line in enumerate(lines):
        if "Available Datasets:" in line:
            datasets_section_idx = i
            # Count spaces before "Available Datasets:"
            indent_level = len(line) - len(line.lstrip())
            break
    
    if datasets_section_idx is None:
        print("❌ Error: Could not find 'Available Datasets:' section in mkdocs.yml")
        return False
    
    # Find all existing datasets and their positions
    datasets = {}
    i = datasets_section_idx + 1
    while i < len(lines):
        line = lines[i]
        # Check if we're still in the datasets section (same or greater indent)
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent_level and line.strip() and not line.strip().startswith('-'):
            break
        
        # Extract dataset info if it's a dataset line
        if 'reference/datasets_documentation/dataset_' in line:
            # Parse the line to get the display name
            match = re.search(r'- ([^:]+):', line)
            if match:
                display_name = match.group(1).strip()
                datasets[display_name] = i
        i += 1
    
    # Add new dataset in alphabetical order
    new_entry = f"{' ' * (indent_level + 2)}- {dataset_name}: {doc_ref}\n"
    
    # Find insertion point
    insert_idx = datasets_section_idx + 1
    for name, idx in sorted(datasets.items()):
        if dataset_name < name:
            insert_idx = idx
            break
        insert_idx = idx + 1
    
    # Insert the new entry
    lines.insert(insert_idx, new_entry)
    
    # Write back the updated content
    with open(mkdocs_path, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Added {dataset_name} to mkdocs.yml navigation")
    return True


def add_to_main_page(dataset_name: str, doc_path: Path, validation_status: str) -> None:
    """
    Add dataset card to main index.md page.
    
    Args:
        dataset_name: Display name for the dataset
        doc_path: Path to dataset documentation
        validation_status: Validation status string (e.g., "94.7% Valid")
    """
    index_path = Path(__file__).parent.parent / "docs" / "index.md"
    
    if not index_path.exists():
        print(f"❌ Error: Main index.md not found at {index_path}")
        return
    
    with open(index_path, 'r') as f:
        content = f.read()
    
    # Check if dataset already on main page
    if dataset_name in content:
        print(f"✅ {dataset_name} already on main page")
        return
    
    # Find the datasets section or create it
    datasets_marker = "## Available Datasets"
    if datasets_marker not in content:
        # Add datasets section before the first ## or at the end
        insert_pos = content.find("\n##")
        if insert_pos == -1:
            content += f"\n\n{datasets_marker}\n\n"
        else:
            content = content[:insert_pos] + f"\n\n{datasets_marker}\n\n" + content[insert_pos:]
    
    # Create dataset card
    doc_rel_path = doc_path.relative_to(Path(__file__).parent.parent / "docs")
    card = f"""\n### {dataset_name}
- **Status**: {validation_status}
- [View Documentation]({doc_rel_path})
"""
    
    # Insert after datasets marker
    marker_pos = content.find(datasets_marker)
    insert_pos = content.find("\n", marker_pos) + 1
    
    # Find next section or end
    next_section = content.find("\n##", insert_pos)
    if next_section == -1:
        content = content[:insert_pos] + card + content[insert_pos:]
    else:
        content = content[:next_section] + card + content[next_section:]
    
    with open(index_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Added {dataset_name} to main page")


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
  Single dataset validation:
    python create_dataset_validation_report.py --datasets converted_datasets/umich_2021_phase.parquet
    
  Multiple datasets validation:
    python create_dataset_validation_report.py --datasets umich_2021_phase.parquet gtech_2021_phase.parquet
    
  All phase datasets with glob pattern:
    python create_dataset_validation_report.py --datasets "converted_datasets/*_phase.parquet"
    
  With custom validation ranges file:
    python create_dataset_validation_report.py --datasets my_data.parquet --ranges-file custom_ranges.yaml
    
  Generate standalone report (old behavior):
    python create_dataset_validation_report.py --datasets my_data.parquet --no-merge
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--datasets", 
        required=True,
        nargs='+',
        help="Path(s) to phase-indexed dataset parquet file(s). Supports glob patterns."
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
        help="Short code for dataset (e.g., UM21 for UMich 2021, GT23 for Georgia Tech 2023). Required for new datasets."
    )
    
    parser.add_argument(
        "--promote-to-main",
        action="store_true",
        help="Promote dataset to main page (requires complete documentation with no TODOs)"
    )
    
    parser.add_argument(
        "--no-comparison",
        action="store_true",
        help="Skip comparison plot generation (only generate validation plots)"
    )
    
    parser.add_argument(
        "--show-plots",
        action="store_true", 
        help="Show matplotlib plots interactively instead of generating markdown report"
    )
    
    parser.add_argument(
        "--show-local-passing",
        action="store_true",
        help="Show locally passing strides in yellow/gold (strides that pass current feature but fail others)"
    )
    
    args = parser.parse_args()
    
    # Expand glob patterns and validate input files
    dataset_paths = []
    for pattern in args.datasets:
        # Check if it's a glob pattern or direct path
        matches = glob.glob(pattern)
        if matches:
            dataset_paths.extend([Path(p) for p in matches])
        else:
            # Try as direct path
            p = Path(pattern)
            if p.exists():
                dataset_paths.append(p)
            else:
                print(f"❌ Error: No files found matching: {pattern}")
                return 1
    
    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for p in dataset_paths:
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)
    dataset_paths = unique_paths
    
    if not dataset_paths:
        print(f"❌ Error: No valid dataset files found")
        return 1
    
    # Determine if batch mode (multiple datasets)
    batch_mode = len(dataset_paths) > 1
    
    if batch_mode:
        print(f"🚀 Dataset Validation Report Generator (Batch Mode)")
        print(f"📂 Processing {len(dataset_paths)} datasets")
    else:
        print(f"🚀 Dataset Validation Report Generator")
    
    # Process configuration once for all datasets
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
    
    # Initialize report generator once
    print(f"\n🔍 Initializing report generator...")
    report_generator = ValidationReportGenerator(ranges_file=str(ranges_file))
    
    # Store results for summary
    batch_results = []
    
    # Process each dataset
    for idx, dataset_path in enumerate(dataset_paths, 1):
        # Show progress for batch mode
        if batch_mode:
            print(f"\n[{idx}/{len(dataset_paths)}] Processing: {dataset_path.name}")
            print("="*60)
        
        # Extract dataset name for display
        dataset_name = dataset_path.stem.replace("_phase", "").replace("_time", "")
        dataset_display_name = dataset_name.replace("_", " ").title()
        
        if not batch_mode:
            print(f"📂 Dataset: {dataset_path}")
        print(f"📝 Report Name: {dataset_display_name}")
        
        # Check if dataset documentation exists
        doc_name = dataset_name
        doc_path = Path(__file__).parent.parent / "docs" / "reference" / "datasets_documentation" / f"dataset_{doc_name}.md"
        doc_exists = doc_path.exists()
    
        # Check for short code requirements and collisions
        existing_codes = get_existing_short_codes()
        
        if not doc_exists and not args.short_code:
            print(f"\n❌ Error: Dataset documentation does not exist at {doc_path}")
            print(f"   A short code is required to create new dataset documentation.")
            print(f"   Please provide --short-code (e.g., --short-code GT21)")
            print(f"\n📋 Existing short codes: {', '.join(sorted(existing_codes.keys()))}")
            if batch_mode:
                print(f"⚠️  Skipping {dataset_path.name}")
                continue
            return 1
        
        if args.short_code:
            if args.short_code in existing_codes:
                print(f"\n❌ Error: Short code '{args.short_code}' is already used by {existing_codes[args.short_code]}")
                print(f"📋 Existing short codes: {', '.join(sorted(existing_codes.keys()))}")
                if batch_mode:
                    print(f"⚠️  Skipping {dataset_path.name}")
                    continue
                return 1
            print(f"✅ Short code '{args.short_code}' is available")
        
        try:
            
            if args.show_plots:
                # Show matplotlib plots interactively using existing plot generation
                print(f"🔍 Running validation (interactive plots mode)...")
                
                # Run validation to get results
                validation_result = report_generator.validator.validate(str(dataset_path))
                
                # Generate plots interactively (don't save to files)
                plot_paths, velocity_results = report_generator._generate_plots(
                    str(dataset_path), 
                    validation_result, 
                    timestamp="interactive",
                    show_interactive=True,
                    show_local_passing=args.show_local_passing
                )
                
                print(f"✅ Interactive plot display complete! Showed plots for {len(plot_paths)} tasks.")
                
            elif args.no_merge:
                # Generate standalone validation report (old behavior)
                print(f"🔍 Running validation (standalone mode)...")
                report_path = report_generator.generate_report(str(dataset_path), generate_plots=True)
                
                print(f"✅ Validation complete!")
                print(f"📄 Report saved: {report_path}")
                
                # Update index.md for standalone reports
                report_file = Path(report_path)
                mkdocs_dir = report_file.parent
                
                print(f"📝 Updating documentation index...")
                update_index_file(
                    report_file.name,
                    dataset_display_name,
                    mkdocs_dir
                )
                
                if not batch_mode:
                    print(f"\n🎉 SUCCESS! Standalone report created!")
                    print(f"🌐 View in MkDocs at: /reference/datasets_documentation/validation_reports/")
            else:
                # Merge validation into dataset documentation (new default behavior)
                print(f"🔍 Running validation (merge mode)...")
                doc_path = report_generator.update_dataset_documentation(
                    str(dataset_path), 
                    generate_plots=True,
                    generate_comparison=not args.no_comparison,
                    short_code=args.short_code
                )
                
                # Extract validation results for batch summary
                with open(doc_path, 'r') as f:
                    doc_content = f.read()
                
                # Extract validation percentage
                import re
                match = re.search(r'\*\*Overall Status\*\*[^\|]*\|\s*([\d.]+)%\s*Valid', doc_content)
                if match:
                    pass_rate = float(match.group(1))
                    if pass_rate >= 95:
                        status = "✅ PASSED"
                    elif pass_rate >= 80:
                        status = "⚠️ PARTIAL"
                    else:
                        status = "❌ FAILED"
                else:
                    pass_rate = 0.0
                    status = "❓ UNKNOWN"
                
                batch_results.append({
                    'name': dataset_display_name,
                    'file': dataset_path.name,
                    'pass_rate': pass_rate,
                    'status': status
                })
                
                print(f"✅ Validation complete! ({pass_rate:.1f}% pass rate)")
                print(f"📄 Documentation updated: {doc_path}")
                
                # Update mkdocs.yml navigation
                doc_filename = f"dataset_{doc_name}"
                update_mkdocs_navigation(dataset_display_name, doc_filename)
                
                # Handle promotion to main page if requested
                if args.promote_to_main:
                    print(f"\n🔍 Checking documentation completeness for main page promotion...")
                    doc_path_obj = Path(doc_path)
                    is_complete, todos = check_documentation_complete(doc_path_obj)
                    
                    if not is_complete:
                        print(f"\n❌ Cannot promote to main page - documentation has {len(todos)} TODO placeholders:")
                        for i, todo in enumerate(todos[:10], 1):  # Show first 10
                            print(f"   {i}. {todo}")
                        if len(todos) > 10:
                            print(f"   ... and {len(todos) - 10} more")
                        print(f"\nPlease complete all TODO items before promoting to main page.")
                        if not batch_mode:
                            return 1
                    else:
                        add_to_main_page(dataset_display_name, doc_path_obj, f"{pass_rate:.1f}% Valid")
                        print(f"🎉 SUCCESS! {dataset_display_name} promoted to main page!")
                
                if not batch_mode:
                    print(f"\n🎉 SUCCESS! Dataset documentation updated with validation!")
                    print(f"🌐 View in MkDocs at: /reference/datasets_documentation/")
        
        except KeyboardInterrupt:
            print(f"\n🛑 Report generation interrupted by user")
            return 1
        except Exception as e:
            print(f"\n❌ Report generation failed for {dataset_path.name}: {e}")
            if batch_mode:
                batch_results.append({
                    'name': dataset_display_name,
                    'file': dataset_path.name,
                    'pass_rate': 0.0,
                    'status': '❌ ERROR'
                })
                continue
            else:
                import traceback
                traceback.print_exc()
                return 1
    
    # Show batch summary if multiple datasets
    if batch_mode and batch_results:
        print("\n" + "="*60)
        print("📊 BATCH SUMMARY:")
        print("╔" + "═"*30 + "╦" + "═"*12 + "╦" + "═"*12 + "╗")
        print("║ {:28} ║ {:10} ║ {:10} ║".format("Dataset", "Pass Rate", "Status"))
        print("╠" + "═"*30 + "╬" + "═"*12 + "╬" + "═"*12 + "╣")
        
        for result in batch_results:
            print("║ {:28} ║ {:9.1f}% ║ {:10} ║".format(
                result['name'][:28], 
                result['pass_rate'],
                result['status'].split()[1] if ' ' in result['status'] else result['status']
            ))
        
        print("╚" + "═"*30 + "╩" + "═"*12 + "╩" + "═"*12 + "╝")
        
        success_count = sum(1 for r in batch_results if r['status'] != '❌ ERROR')
        print(f"\n🎉 SUCCESS! Validated {success_count}/{len(dataset_paths)} datasets")
        print(f"🌐 View in MkDocs at: /reference/datasets_documentation/")
    
    return 0


class TeeOutput:
    """Tee output to both console and file."""
    def __init__(self, *files):
        self.files = files
    
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    
    def flush(self):
        for f in self.files:
            f.flush()

if __name__ == "__main__":
    from datetime import datetime
    import os
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = f"validation_report_log_{timestamp}.txt"
    
    print(f"📋 Logging all output to: {log_file_path}")
    
    # Open log file and set up tee output
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        # Write header
        log_file.write(f"# Validation Report Generation Log\n")
        log_file.write(f"# Started: {datetime.now()}\n")
        log_file.write(f"# Command: {' '.join(sys.argv)}\n")
        log_file.write(f"# Working Directory: {os.getcwd()}\n")
        log_file.write(f"{'='*60}\n\n")
        log_file.flush()
        
        # Set up tee output to both console and file
        tee = TeeOutput(sys.stdout, log_file)
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            sys.stdout = tee
            sys.stderr = tee
            
            print(f"🚀 Starting validation report generation at {datetime.now()}")
            print(f"📋 All output will be logged to: {log_file_path}")
            print("="*60)
            
            exit_code = main()
            
            print("="*60)
            print(f"✅ Report generation completed with exit code: {exit_code}")
            print(f"📋 Full log available at: {log_file_path}")
            
        except Exception as e:
            print(f"💥 FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            exit_code = 1
            
        finally:
            # Restore original outputs
            sys.stdout = original_stdout  
            sys.stderr = original_stderr
            
            # Write footer to log
            log_file.write(f"\n{'='*60}\n")
            log_file.write(f"# Finished: {datetime.now()}\n")
            log_file.write(f"# Exit Code: {exit_code}\n")
    
    print(f"📋 Complete log saved to: {log_file_path}")
    sys.exit(exit_code)