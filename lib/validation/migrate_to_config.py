#!/usr/bin/env python3
"""
Migration Script: Markdown Tables to YAML Config

Migrates validation ranges from markdown files to YAML config files.
This is a one-time migration script to transition from the old markdown-based
storage to the new config-based approach.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from lib.validation.validation_expectations_parser import ValidationExpectationsParser
from lib.validation.config_manager import ValidationConfigManager


def migrate_validation_ranges():
    """
    Migrate validation ranges from markdown files to YAML config files.
    """
    print("🔄 Starting migration from markdown to YAML config files...")
    
    # Initialize parser and config manager
    parser = ValidationExpectationsParser()
    config_manager = ValidationConfigManager()
    
    # Define markdown file paths
    # Try to use test data first (has actual values), fallback to docs if not available
    test_data_dir = project_root / "tests" / "test_data" / "validation_parser"
    docs_dir = project_root / "docs" / "user_guide" / "docs" / "reference" / "standard_spec"
    
    # Check for test data files first (they have actual range values)
    kinematic_test = test_data_dir / "original_kinematic.md"
    kinetic_test = test_data_dir / "original_kinetic.md"
    
    # Use test data if available, otherwise use docs
    kinematic_md = kinematic_test if kinematic_test.exists() else docs_dir / "validation_expectations_kinematic.md"
    kinetic_md = kinetic_test if kinetic_test.exists() else docs_dir / "validation_expectations_kinetic.md"
    
    # Migrate kinematic data
    if kinematic_md.exists():
        print(f"\n📊 Migrating kinematic validation ranges...")
        print(f"   Source: {kinematic_md}")
        
        try:
            # Read from markdown
            kinematic_data = parser.read_validation_data(str(kinematic_md))
            
            # Prepare metadata
            metadata = {
                'source': 'Migrated from validation_expectations_kinematic.md',
                'migration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'description': 'Kinematic validation ranges for joint angles'
            }
            
            # Check if we can extract more metadata from the markdown
            with open(kinematic_md, 'r') as f:
                content = f.read()
                # Look for dataset and method info in the markdown
                if 'umich_2021_phase.parquet' in content:
                    metadata['source_dataset'] = 'umich_2021_phase.parquet'
                if '95% Percentile' in content or '95th percentile' in content.lower():
                    metadata['method'] = '95th percentile'
            
            # Save to YAML config
            config_manager.save_validation_ranges('kinematic', kinematic_data, metadata)
            
            # Report statistics
            task_count = len(kinematic_data)
            var_count = sum(len(variables) for phase_data in next(iter(kinematic_data.values())).values() 
                           for variables in [phase_data])
            print(f"   ✅ Migrated {task_count} tasks with ~{var_count} variables per phase")
            
        except Exception as e:
            print(f"   ❌ Error migrating kinematic data: {e}")
            return False
    else:
        print(f"⚠️  Kinematic markdown file not found: {kinematic_md}")
    
    # Migrate kinetic data
    if kinetic_md.exists():
        print(f"\n📊 Migrating kinetic validation ranges...")
        print(f"   Source: {kinetic_md}")
        
        try:
            # Read from markdown
            kinetic_data = parser.read_validation_data(str(kinetic_md))
            
            # Prepare metadata
            metadata = {
                'source': 'Migrated from validation_expectations_kinetic.md',
                'migration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'description': 'Kinetic validation ranges for forces and moments'
            }
            
            # Check if we can extract more metadata from the markdown
            with open(kinetic_md, 'r') as f:
                content = f.read()
                if 'umich_2021_phase.parquet' in content:
                    metadata['source_dataset'] = 'umich_2021_phase.parquet'
                if '95% Percentile' in content or '95th percentile' in content.lower():
                    metadata['method'] = '95th percentile'
            
            # Save to YAML config
            config_manager.save_validation_ranges('kinetic', kinetic_data, metadata)
            
            # Report statistics
            task_count = len(kinetic_data)
            var_count = sum(len(variables) for phase_data in next(iter(kinetic_data.values())).values() 
                           for variables in [phase_data])
            print(f"   ✅ Migrated {task_count} tasks with ~{var_count} variables per phase")
            
        except Exception as e:
            print(f"   ❌ Error migrating kinetic data: {e}")
            return False
    else:
        print(f"⚠️  Kinetic markdown file not found: {kinetic_md}")
    
    print("\n✅ Migration complete!")
    print(f"   Config files saved to: {config_manager.config_dir}")
    
    # Verify the migration
    print("\n🔍 Verifying migration...")
    
    if config_manager.config_exists('kinematic'):
        kinematic_metadata = config_manager.get_metadata('kinematic')
        print(f"   ✅ Kinematic config: {config_manager.kinematic_config}")
        print(f"      Version: {kinematic_metadata.get('version', 'N/A')}")
        print(f"      Generated: {kinematic_metadata.get('generated', 'N/A')}")
    
    if config_manager.config_exists('kinetic'):
        kinetic_metadata = config_manager.get_metadata('kinetic')
        print(f"   ✅ Kinetic config: {config_manager.kinetic_config}")
        print(f"      Version: {kinetic_metadata.get('version', 'N/A')}")
        print(f"      Generated: {kinetic_metadata.get('generated', 'N/A')}")
    
    return True


if __name__ == "__main__":
    success = migrate_validation_ranges()
    sys.exit(0 if success else 1)