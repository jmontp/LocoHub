#!/usr/bin/env python3
"""
Update Validation Ranges CLI

Created: 2025-06-18 with user permission
Purpose: Simple CLI for updating validation ranges with literature tracking

Intent: Provides a memory-efficient command-line interface for updating validation
ranges with proper tracking, version control, and rollback capabilities. Uses
minimal dependencies and simple data structures for optimal performance.
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from lib.validation.range_updater import RangeUpdater, RangeUpdate, create_range_update_from_input
from lib.core.feature_constants import get_feature_list


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Update validation ranges with literature citations and version control',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update a single range
  python update_validation_ranges.py update \\
    --file docs/standard_spec/validation_expectations_kinematic.md \\
    --task level_walking --phase 0 --variable hip_flexion_angle_ipsi \\
    --min -0.15 --max 0.35 \\
    --citation "Smith et al. 2023" \\
    --rationale "Updated based on larger dataset" \\
    --reviewer "john_doe"

  # View version history
  python update_validation_ranges.py history \\
    --version-file versions/kinematic_versions.json

  # Rollback to previous version
  python update_validation_ranges.py rollback \\
    --file docs/standard_spec/validation_expectations_kinematic.md \\
    --version-file versions/kinematic_versions.json \\
    --version 5

  # Interactive mode
  python update_validation_ranges.py interactive \\
    --file docs/standard_spec/validation_expectations_kinematic.md
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update a single validation range')
    update_parser.add_argument('--file', required=True, help='Validation expectations file to update')
    update_parser.add_argument('--task', required=True, help='Task name (e.g., level_walking)')
    update_parser.add_argument('--phase', type=int, required=True, help='Phase percentage (0, 25, 50, 75)')
    update_parser.add_argument('--variable', required=True, help='Variable name (e.g., hip_flexion_angle_ipsi)')
    update_parser.add_argument('--min', type=float, required=True, help='New minimum value')
    update_parser.add_argument('--max', type=float, required=True, help='New maximum value')
    update_parser.add_argument('--citation', required=True, help='Literature citation')
    update_parser.add_argument('--rationale', required=True, help='Rationale for the change')
    update_parser.add_argument('--reviewer', required=True, help='Name/ID of reviewer')
    update_parser.add_argument('--version-file', help='Version tracking file (optional)')
    
    # Batch update command
    batch_parser = subparsers.add_parser('batch', help='Apply multiple updates from JSON file')
    batch_parser.add_argument('--file', required=True, help='Validation expectations file to update')
    batch_parser.add_argument('--updates-file', required=True, help='JSON file with batch updates')
    batch_parser.add_argument('--version-file', help='Version tracking file (optional)')
    
    # History command
    history_parser = subparsers.add_parser('history', help='View version history')
    history_parser.add_argument('--version-file', required=True, help='Version tracking file')
    history_parser.add_argument('--task', help='Filter by task (optional)')
    history_parser.add_argument('--variable', help='Filter by variable (optional)')
    history_parser.add_argument('--limit', type=int, default=20, help='Maximum number of entries to show')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to previous version')
    rollback_parser.add_argument('--file', required=True, help='Validation expectations file to update')
    rollback_parser.add_argument('--version-file', required=True, help='Version tracking file')
    rollback_parser.add_argument('--version', type=int, required=True, help='Version number to rollback to')
    rollback_parser.add_argument('--reviewer', required=True, help='Name/ID of reviewer performing rollback')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive update mode')
    interactive_parser.add_argument('--file', required=True, help='Validation expectations file to update')
    interactive_parser.add_argument('--version-file', help='Version tracking file (optional)')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show information about validation file')
    info_parser.add_argument('--file', required=True, help='Validation expectations file to analyze')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'update':
            handle_update(args)
        elif args.command == 'batch':
            handle_batch(args)
        elif args.command == 'history':
            handle_history(args)
        elif args.command == 'rollback':
            handle_rollback(args)
        elif args.command == 'interactive':
            handle_interactive(args)
        elif args.command == 'info':
            handle_info(args)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_update(args):
    """Handle single range update command."""
    updater = RangeUpdater()
    
    # Validate file exists
    if not Path(args.file).exists():
        raise FileNotFoundError(f"Validation file not found: {args.file}")
    
    # Create range update
    update = create_range_update_from_input(
        task=args.task,
        phase=args.phase,
        variable=args.variable,
        new_min=args.min,
        new_max=args.max,
        citation=args.citation,
        rationale=args.rationale,
        reviewer=args.reviewer
    )
    
    # Apply update
    print(f"Updating {args.task}.{args.phase}.{args.variable}: [{args.min}, {args.max}]")
    print(f"Citation: {args.citation}")
    print(f"Rationale: {args.rationale}")
    
    updater.update_validation_file(args.file, [update], args.version_file)
    
    print("✅ Update applied successfully")
    
    if args.version_file:
        print(f"📝 Version tracked in {args.version_file}")


def handle_batch(args):
    """Handle batch update command."""
    updater = RangeUpdater()
    
    # Validate files exist
    if not Path(args.file).exists():
        raise FileNotFoundError(f"Validation file not found: {args.file}")
    if not Path(args.updates_file).exists():
        raise FileNotFoundError(f"Updates file not found: {args.updates_file}")
    
    # Load batch updates
    with open(args.updates_file, 'r') as f:
        batch_data = json.load(f)
    
    updates = []
    for update_data in batch_data['updates']:
        update = RangeUpdate.from_dict(update_data)
        updates.append(update)
    
    print(f"Applying {len(updates)} batch updates...")
    
    # Check for conflicts
    conflicts = updater.detect_conflicts(updates)
    if conflicts:
        print("❌ Conflicts detected:")
        for conflict in conflicts:
            print(f"  - {conflict['task']}.{conflict['phase']}.{conflict['variable']}: {conflict['type']}")
        raise ValueError("Resolve conflicts before applying batch updates")
    
    # Apply updates
    updater.update_validation_file(args.file, updates, args.version_file)
    
    print("✅ Batch updates applied successfully")


def handle_history(args):
    """Handle version history command."""
    updater = RangeUpdater()
    
    if not Path(args.version_file).exists():
        print("No version history found")
        return
    
    history = updater.get_version_history(
        args.version_file, 
        task=args.task, 
        variable=args.variable
    )
    
    if not history:
        print("No version history found matching filters")
        return
    
    print(f"📋 Version History ({len(history)} entries):")
    print()
    
    for i, entry in enumerate(history[:args.limit]):
        timestamp = datetime.fromisoformat(entry['timestamp'])
        print(f"Version {entry['version']} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Task: {entry['task']}, Phase: {entry['phase']}%, Variable: {entry['variable']}")
        print(f"  Change: [{entry['old_min']:.3f}, {entry['old_max']:.3f}] → [{entry['new_min']:.3f}, {entry['new_max']:.3f}]")
        print(f"  Citation: {entry['citation']}")
        print(f"  Rationale: {entry['rationale']}")
        print(f"  Reviewer: {entry['reviewer']}")
        print()


def handle_rollback(args):
    """Handle rollback command."""
    updater = RangeUpdater()
    
    if not Path(args.version_file).exists():
        raise FileNotFoundError(f"Version file not found: {args.version_file}")
    
    # Get rollback update
    rollback_update = updater.get_rollback_update(args.version_file, args.version)
    rollback_update.reviewer = args.reviewer
    
    print(f"Rolling back to version {args.version}:")
    print(f"  {rollback_update.task}.{rollback_update.phase}.{rollback_update.variable}")
    print(f"  New range: [{rollback_update.new_min:.3f}, {rollback_update.new_max:.3f}]")
    
    # Confirm rollback
    confirm = input("Continue with rollback? (y/N): ")
    if confirm.lower() != 'y':
        print("Rollback cancelled")
        return
    
    # Apply rollback
    updater.update_validation_file(args.file, [rollback_update], args.version_file)
    
    print("✅ Rollback completed successfully")


def handle_interactive(args):
    """Handle interactive update mode."""
    updater = RangeUpdater()
    
    # Validate file exists
    if not Path(args.file).exists():
        raise FileNotFoundError(f"Validation file not found: {args.file}")
    
    print("🔧 Interactive Validation Range Update")
    print("=" * 40)
    
    # Load current data to show available options
    validation_data = updater.load_validation_data(args.file)
    
    print("Available tasks:")
    for task in validation_data.keys():
        print(f"  - {task}")
    print()
    
    # Get user input
    task = input("Task name: ").strip()
    if task not in validation_data:
        raise ValueError(f"Task '{task}' not found")
    
    print("Available phases:")
    for phase in sorted(validation_data[task].keys()):
        print(f"  - {phase}%")
    print()
    
    phase = int(input("Phase (0, 25, 50, 75): ").strip())
    if phase not in validation_data[task]:
        raise ValueError(f"Phase {phase} not found for task '{task}'")
    
    print("Available variables:")
    for var in validation_data[task][phase].keys():
        current_range = validation_data[task][phase][var]
        print(f"  - {var}: [{current_range['min']:.3f}, {current_range['max']:.3f}]")
    print()
    
    variable = input("Variable name: ").strip()
    if variable not in validation_data[task][phase]:
        raise ValueError(f"Variable '{variable}' not found")
    
    # Show current range
    current_range = validation_data[task][phase][variable]
    print(f"\nCurrent range: [{current_range['min']:.3f}, {current_range['max']:.3f}]")
    
    # Get new range
    new_min = float(input("New minimum value: ").strip())
    new_max = float(input("New maximum value: ").strip())
    
    if new_min > new_max:
        raise ValueError("Minimum value cannot be greater than maximum value")
    
    # Get metadata
    citation = input("Literature citation: ").strip()
    rationale = input("Rationale for change: ").strip()
    reviewer = input("Your name/ID: ").strip()
    
    # Create and apply update
    update = create_range_update_from_input(
        task=task,
        phase=phase,
        variable=variable,
        new_min=new_min,
        new_max=new_max,
        citation=citation,
        rationale=rationale,
        reviewer=reviewer
    )
    
    print("\n📋 Update Summary:")
    print(f"  Task: {task}")
    print(f"  Phase: {phase}%")
    print(f"  Variable: {variable}")
    print(f"  Change: [{current_range['min']:.3f}, {current_range['max']:.3f}] → [{new_min:.3f}, {new_max:.3f}]")
    print(f"  Citation: {citation}")
    print(f"  Rationale: {rationale}")
    print()
    
    confirm = input("Apply update? (y/N): ")
    if confirm.lower() != 'y':
        print("Update cancelled")
        return
    
    updater.update_validation_file(args.file, [update], args.version_file)
    
    print("✅ Update applied successfully")


def handle_info(args):
    """Handle info command."""
    updater = RangeUpdater()
    
    if not Path(args.file).exists():
        raise FileNotFoundError(f"Validation file not found: {args.file}")
    
    # Load validation data
    validation_data = updater.load_validation_data(args.file)
    
    print(f"📊 Validation File Info: {args.file}")
    print("=" * 50)
    
    # Count statistics
    total_tasks = len(validation_data)
    total_phases = sum(len(task_data) for task_data in validation_data.values())
    total_variables = sum(
        len(phase_data) 
        for task_data in validation_data.values() 
        for phase_data in task_data.values()
    )
    
    print(f"Tasks: {total_tasks}")
    print(f"Phases: {total_phases}")
    print(f"Variables: {total_variables}")
    print()
    
    # Show task breakdown
    for task, task_data in validation_data.items():
        print(f"Task: {task}")
        for phase in sorted(task_data.keys()):
            variables = list(task_data[phase].keys())
            print(f"  Phase {phase}%: {len(variables)} variables")
            for var in variables[:3]:  # Show first 3 variables
                range_data = task_data[phase][var]
                print(f"    - {var}: [{range_data['min']:.3f}, {range_data['max']:.3f}]")
            if len(variables) > 3:
                print(f"    ... and {len(variables) - 3} more")
        print()


if __name__ == '__main__':
    main()