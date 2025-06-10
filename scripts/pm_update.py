#!/usr/bin/env python3
"""
PM Update Script for Locomotion Data Standardization

Manages the hierarchical PM structure:
1. Migrates work items from component PM_ongoing.md files to PM_history.md when exceeding 15 items
2. Reconstructs PM_snapshot.md from component PM_ongoing.md high-level tasks

Usage:
    python scripts/pm_update.py --check                          # Check all component PM files from registry
    python scripts/pm_update.py --verify                         # Verify and auto-adjust all PM files from registry
    python scripts/pm_update.py --migrate component/             # Migrate specific component  
    python scripts/pm_update.py --migrate-all                    # Migrate all components needing it
    python scripts/pm_update.py --rebuild-snapshot               # Reconstruct PM_snapshot.md from components
    python scripts/pm_update.py --full-update                    # Complete workflow: verify + rebuild snapshot
    python scripts/pm_update.py --full-update --dry-run          # Preview complete workflow without executing
"""

import argparse
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# Component information for this project
component_info = {
    'docs/standard_spec': {
        'name': 'Standard Specification',
        'path': 'docs/standard_spec/',
        'description': 'Core data standardization specification and validation rules'
    },
    'source/conversion_scripts': {
        'name': 'Data Conversion Scripts',
        'path': 'source/conversion_scripts/',
        'description': 'Dataset conversion tools and scripts'
    },
    'source/tests': {
        'name': 'Testing & Validation',
        'path': 'source/tests/',
        'description': 'Validation systems and test suites'
    },
    'source/visualization': {
        'name': 'Visualization Tools',
        'path': 'source/visualization/',
        'description': 'Data visualization and plotting tools'
    }
}


def read_claude_md_registry() -> List[str]:
    """
    Read PM file registry from CLAUDE.md
    
    Returns:
        List of PM file paths from registry
    """
    claude_md_path = Path("CLAUDE.md")
    if not claude_md_path.exists():
        print("⚠️  CLAUDE.md not found, using fallback component discovery")
        return []
    
    registry_files = []
    try:
        with open(claude_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for registry section
        registry_match = re.search(
            r'### Distributed PM Files Registry.*?(?=###|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if registry_match:
            registry_section = registry_match.group(0)
            # Extract PM file paths
            pm_file_matches = re.findall(r'- `([^`]+/PM_ongoing\.md)`', registry_section)
            registry_files = pm_file_matches
            
    except Exception as e:
        print(f"⚠️  Error reading CLAUDE.md registry: {e}")
    
    return registry_files


def discover_pm_files() -> List[str]:
    """
    Discover PM_ongoing.md files as fallback if registry unavailable
    
    Returns:
        List of discovered PM file paths
    """
    pm_files = []
    for root, dirs, files in os.walk('.'):
        if 'PM_ongoing.md' in files:
            pm_path = os.path.join(root, 'PM_ongoing.md').replace('./', '')
            pm_files.append(pm_path)
    
    return pm_files


def get_pm_files() -> List[str]:
    """
    Get PM files from registry or fallback discovery
    
    Returns:
        List of PM file paths to process
    """
    registry_files = read_claude_md_registry()
    
    if registry_files:
        print(f"📋 Found {len(registry_files)} PM files in CLAUDE.md registry")
        return registry_files
    else:
        discovered_files = discover_pm_files()
        print(f"🔍 Discovered {len(discovered_files)} PM files via fallback")
        return discovered_files


def parse_pm_ongoing(file_path: str) -> Dict:
    """
    Parse a PM_ongoing.md file structure
    
    Args:
        file_path: Path to PM_ongoing.md file
        
    Returns:
        Dict with parsed content structure
    """
    if not os.path.exists(file_path):
        return {
            'exists': False,
            'high_level_tasks': [],
            'recent_work_count': 0,
            'needs_migration': False,
            'content': ''
        }
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract high-level tasks
    high_level_tasks = extract_high_level_tasks(content)
    
    # Count recent work items
    recent_work_count = count_recent_work_items(content)
    
    # Determine if migration needed (>15 items)
    needs_migration = recent_work_count > 15
    
    return {
        'exists': True,
        'high_level_tasks': high_level_tasks,
        'recent_work_count': recent_work_count,
        'needs_migration': needs_migration,
        'content': content,
        'file_path': file_path
    }


def extract_high_level_tasks(content: str) -> List[Dict]:
    """
    Extract high-level tasks from PM_ongoing.md content
    
    Args:
        content: File content
        
    Returns:
        List of task dictionaries
    """
    tasks = []
    
    # Find High Level Tasks section
    high_level_match = re.search(
        r'## High Level Tasks\s*\n(.*?)(?=\n##|\Z)',
        content,
        re.DOTALL
    )
    
    if not high_level_match:
        return tasks
    
    tasks_section = high_level_match.group(1)
    
    # Extract individual tasks
    task_matches = re.finditer(
        r'### \d+\.\s*(.+?)\n(.*?)(?=\n###|\Z)',
        tasks_section,
        re.DOTALL
    )
    
    for match in task_matches:
        task_name = match.group(1).strip()
        task_content = match.group(2).strip()
        
        # Extract description and status
        description = ""
        status = ""
        
        desc_match = re.search(r'- \*\*Description\*\*:\s*(.+)', task_content)
        if desc_match:
            description = desc_match.group(1).strip()
        
        status_match = re.search(r'- \*\*Status\*\*:\s*(.+)', task_content)
        if status_match:
            status = status_match.group(1).strip()
        
        tasks.append({
            'name': task_name,
            'description': description,
            'status': status
        })
    
    return tasks


def count_recent_work_items(content: str) -> int:
    """
    Count items in Recent Work section
    
    Args:
        content: File content
        
    Returns:
        Number of recent work items
    """
    # Find Recent Work section
    recent_work_match = re.search(
        r'## Recent Work.*?\n(.*?)(?=\n##|\Z)',
        content,
        re.DOTALL
    )
    
    if not recent_work_match:
        return 0
    
    recent_work_section = recent_work_match.group(1)
    
    # Count numbered items (format: "N. **[Title]**")
    item_matches = re.finditer(r'^\d+\.\s*\*\*', recent_work_section, re.MULTILINE)
    return len(list(item_matches))


def migrate_pm_file(file_path: str, dry_run: bool = False) -> bool:
    """
    Migrate excess work items from PM_ongoing.md to PM_history.md
    
    Args:
        file_path: Path to PM_ongoing.md file
        dry_run: If True, don't actually modify files
        
    Returns:
        True if migration was performed
    """
    parsed = parse_pm_ongoing(file_path)
    
    if not parsed['exists'] or not parsed['needs_migration']:
        return False
    
    print(f"📦 Migrating {file_path} ({parsed['recent_work_count']} items)")
    
    if dry_run:
        print(f"   [DRY RUN] Would migrate {parsed['recent_work_count'] - 10} items")
        return True
    
    # Extract content sections
    content = parsed['content']
    
    # Find Recent Work section
    recent_work_match = re.search(
        r'(## Recent Work.*?\n)(.*?)(\n##|\Z)',
        content,
        re.DOTALL
    )
    
    if not recent_work_match:
        print(f"   ⚠️  Could not find Recent Work section in {file_path}")
        return False
    
    recent_work_header = recent_work_match.group(1)
    recent_work_content = recent_work_match.group(2)
    remaining_content = recent_work_match.group(3) if recent_work_match.group(3) else ""
    
    # Split work items
    items = re.findall(r'(\d+\.\s*\*\*.*?(?=\d+\.\s*\*\*|\Z))', recent_work_content, re.DOTALL)
    
    if len(items) <= 15:
        return False
    
    # Keep last 10 items, migrate the rest
    items_to_migrate = items[:-10]
    items_to_keep = items[-10:]
    
    # Create migrated content
    timestamp = datetime.now().strftime('%Y-%m-%d')
    migrated_content = f"\n## Migrated Items - {timestamp}\n\n"
    migrated_content += "".join(items_to_migrate)
    
    # Update PM_ongoing.md with remaining items
    new_recent_work = "".join(items_to_keep)
    new_content = content.replace(
        recent_work_match.group(0),
        recent_work_header + new_recent_work + remaining_content
    )
    
    # Write updated PM_ongoing.md
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # Append to PM_history.md
    history_path = file_path.replace('PM_ongoing.md', 'PM_history.md')
    
    if os.path.exists(history_path):
        with open(history_path, 'r', encoding='utf-8') as f:
            existing_history = f.read()
        
        # Insert new migration at the top (after title)
        title_match = re.search(r'(# PM HISTORY.*?\n\n)', existing_history, re.DOTALL)
        if title_match:
            new_history = title_match.group(1) + migrated_content + "\n" + existing_history[len(title_match.group(1)):]
        else:
            new_history = migrated_content + "\n" + existing_history
    else:
        # Create new PM_history.md
        component_name = get_component_name(file_path)
        new_history = f"# PM HISTORY - {component_name}\n\n{migrated_content}"
    
    with open(history_path, 'w', encoding='utf-8') as f:
        f.write(new_history)
    
    print(f"   ✅ Migrated {len(items_to_migrate)} items to {history_path}")
    print(f"   ✅ Kept {len(items_to_keep)} recent items in {file_path}")
    
    return True


def get_component_name(file_path: str) -> str:
    """
    Get component name from file path
    
    Args:
        file_path: Path to PM file
        
    Returns:
        Component display name
    """
    dir_path = os.path.dirname(file_path)
    
    if dir_path in component_info:
        return component_info[dir_path]['name']
    
    # Fallback to directory name
    return os.path.basename(dir_path).replace('_', ' ').title()


def reconstruct_pm_snapshot(dry_run: bool = False) -> bool:
    """
    Reconstruct PM_snapshot.md from all component PM_ongoing.md files
    
    Args:
        dry_run: If True, don't write file
        
    Returns:
        True if reconstruction was performed
    """
    pm_files = get_pm_files()
    
    if not pm_files:
        print("⚠️  No PM files found for snapshot reconstruction")
        return False
    
    print(f"🏗️  Reconstructing PM_snapshot.md from {len(pm_files)} component files")
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Build snapshot content
    snapshot_content = f"""# PM SNAPSHOT - Locomotion Data Standardization

*High-level project overview auto-constructed from component PM files*
*Last updated: {timestamp}*

## PM Summary
**Tracked PM Files**: {len(pm_files)} component PM_ongoing.md files
**Component Paths**:
"""
    
    for pm_file in pm_files:
        snapshot_content += f"- `{pm_file}`\n"
    
    snapshot_content += "\n## Project Components\n\n"
    
    # Process each component
    for i, pm_file in enumerate(pm_files, 1):
        parsed = parse_pm_ongoing(pm_file)
        dir_path = os.path.dirname(pm_file)
        component_name = get_component_name(pm_file)
        
        snapshot_content += f"### {i}. {component_name} (`{dir_path}/`)\n"
        snapshot_content += f"- **PM File**: [{pm_file}](./{pm_file})\n"
        
        if parsed['exists'] and parsed['high_level_tasks']:
            snapshot_content += "- **High Level Tasks**:\n"
            for task in parsed['high_level_tasks']:
                snapshot_content += f"  - {task['name']}\n"
            
            status = "✅ ACTIVE" if parsed['recent_work_count'] > 0 else "💤 IDLE"
            snapshot_content += f"- **Status**: {status} ({parsed['recent_work_count']} recent work items)\n\n"
        else:
            snapshot_content += "- **Status**: ⚠️ NO PM FILE\n\n"
    
    snapshot_content += f"\n<!-- Auto-generated by scripts/pm_update.py on {timestamp} -->\n"
    
    if dry_run:
        print("   [DRY RUN] Would write PM_snapshot.md:")
        print("   " + "\n   ".join(snapshot_content.split('\n')[:10]) + "...")
        return True
    
    # Write PM_snapshot.md
    with open('PM_snapshot.md', 'w', encoding='utf-8') as f:
        f.write(snapshot_content)
    
    print(f"   ✅ Reconstructed PM_snapshot.md with {len(pm_files)} components")
    return True


def check_pm_files():
    """Check status of all PM files from registry"""
    pm_files = get_pm_files()
    
    print(f"📊 PM Files Status Check")
    print("=" * 40)
    
    total_items = 0
    needs_migration = []
    
    for pm_file in pm_files:
        parsed = parse_pm_ongoing(pm_file)
        component_name = get_component_name(pm_file)
        
        if parsed['exists']:
            status = "✅ OK"
            if parsed['needs_migration']:
                status = "⚠️ MIGRATION NEEDED"
                needs_migration.append(pm_file)
            
            print(f"  {component_name:25} | {parsed['recent_work_count']:2d} items | {status}")
            total_items += parsed['recent_work_count']
        else:
            print(f"  {component_name:25} | -- items | ❌ MISSING")
    
    print("=" * 40)
    print(f"Total work items: {total_items}")
    
    if needs_migration:
        print(f"\n⚠️  {len(needs_migration)} components need migration:")
        for pm_file in needs_migration:
            print(f"   - {pm_file}")


def main():
    parser = argparse.ArgumentParser(description='PM Update Script for Locomotion Data Standardization')
    parser.add_argument('--check', action='store_true', help='Check all component PM files from registry')
    parser.add_argument('--verify', action='store_true', help='Verify and auto-adjust all PM files from registry')
    parser.add_argument('--migrate', type=str, help='Migrate specific component (e.g., docs/standard_spec/)')
    parser.add_argument('--migrate-all', action='store_true', help='Migrate all components needing it')
    parser.add_argument('--rebuild-snapshot', action='store_true', help='Reconstruct PM_snapshot.md from components')
    parser.add_argument('--full-update', action='store_true', help='Complete workflow: verify + rebuild snapshot')
    parser.add_argument('--dry-run', action='store_true', help='Preview operations without executing')
    
    args = parser.parse_args()
    
    if args.check:
        check_pm_files()
    
    elif args.verify:
        pm_files = get_pm_files()
        for pm_file in pm_files:
            parsed = parse_pm_ongoing(pm_file)
            if parsed['needs_migration']:
                migrate_pm_file(pm_file, dry_run=args.dry_run)
    
    elif args.migrate:
        pm_file = os.path.join(args.migrate, 'PM_ongoing.md')
        migrate_pm_file(pm_file, dry_run=args.dry_run)
    
    elif args.migrate_all:
        pm_files = get_pm_files()
        migrated_count = 0
        for pm_file in pm_files:
            if migrate_pm_file(pm_file, dry_run=args.dry_run):
                migrated_count += 1
        print(f"📦 Migration complete: {migrated_count} components migrated")
    
    elif args.rebuild_snapshot:
        reconstruct_pm_snapshot(dry_run=args.dry_run)
    
    elif args.full_update:
        print("🔄 Full PM Update")
        print("=" * 20)
        
        # Step 1: Check and migrate
        pm_files = get_pm_files()
        migrated_count = 0
        for pm_file in pm_files:
            if migrate_pm_file(pm_file, dry_run=args.dry_run):
                migrated_count += 1
        
        if migrated_count > 0:
            print(f"📦 Migrated {migrated_count} components")
        
        # Step 2: Rebuild snapshot
        reconstruct_pm_snapshot(dry_run=args.dry_run)
        
        print("✅ Full PM update complete")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()