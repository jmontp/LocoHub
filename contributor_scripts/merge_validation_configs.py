#!/usr/bin/env python3
"""
Script to merge kinematic and kinetic validation YAML files into a single consolidated file.
"""

import yaml
from pathlib import Path
from datetime import datetime

def merge_validation_configs():
    """Merge kinematic and kinetic validation YAML files."""
    
    # Load both YAML files
    config_dir = Path(__file__).parent / "validation_ranges"
    
    with open(config_dir / "kinematic_ranges.yaml", 'r') as f:
        kinematic_data = yaml.safe_load(f)
    
    with open(config_dir / "kinetic_ranges.yaml", 'r') as f:
        kinetic_data = yaml.safe_load(f)
    
    # Create consolidated structure
    consolidated = {
        'version': '2.0',
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': 'Consolidated from kinematic_ranges.yaml and kinetic_ranges.yaml',
        'migration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'description': 'Consolidated validation ranges for all biomechanical features',
        'source_dataset': kinematic_data['source_dataset'],
        'method': kinematic_data['method'],
        'feature_types': {
            'kinematic': ['angles', 'velocities'],
            'kinetic': ['moments', 'forces']
        },
        'tasks': {}
    }
    
    # Merge tasks
    all_tasks = set(kinematic_data['tasks'].keys()) | set(kinetic_data['tasks'].keys())
    
    for task in all_tasks:
        consolidated['tasks'][task] = {'phases': {}}
        
        # Get phases from both configs
        kin_phases = kinematic_data['tasks'].get(task, {}).get('phases', {}) if task in kinematic_data['tasks'] else {}
        knt_phases = kinetic_data['tasks'].get(task, {}).get('phases', {}) if task in kinetic_data['tasks'] else {}
        
        all_phases = set(kin_phases.keys()) | set(knt_phases.keys())
        
        for phase in all_phases:
            phase_data = {}
            
            # Add kinematic features (already without _rad suffix in YAML)
            if phase in kin_phases:
                for var, ranges in kin_phases[phase].items():
                    # Add _rad suffix back for angles
                    if 'angle' in var and not var.endswith('_rad'):
                        var_with_unit = f"{var}_rad"
                    elif 'velocity' in var and not var.endswith('_rad_s'):
                        var_with_unit = f"{var}_rad_s"
                    else:
                        var_with_unit = var
                    phase_data[var_with_unit] = ranges
            
            # Add kinetic features (already without _Nm suffix in YAML)
            if phase in knt_phases:
                for var, ranges in knt_phases[phase].items():
                    # Add _Nm suffix back for moments
                    if 'moment' in var and not var.endswith('_Nm'):
                        var_with_unit = f"{var}_Nm"
                    elif 'force' in var or 'grf' in var and not var.endswith('_N'):
                        var_with_unit = f"{var}_N"
                    else:
                        var_with_unit = var
                    phase_data[var_with_unit] = ranges
            
            # Sort variables for consistent ordering
            sorted_vars = {}
            # First add kinematic variables (angles, velocities)
            for var in sorted(phase_data.keys()):
                if 'angle' in var or 'velocity' in var:
                    sorted_vars[var] = phase_data[var]
            # Then add kinetic variables (moments, forces)
            for var in sorted(phase_data.keys()):
                if 'moment' in var or 'force' in var or 'grf' in var:
                    sorted_vars[var] = phase_data[var]
            
            consolidated['tasks'][task]['phases'][phase] = sorted_vars
    
    # Write consolidated file
    output_path = config_dir / "validation_ranges.yaml"
    with open(output_path, 'w') as f:
        yaml.dump(consolidated, f, default_flow_style=False, sort_keys=False, width=120)
    
    print(f"✅ Created consolidated validation config: {output_path}")
    print(f"   - Tasks: {len(consolidated['tasks'])}")
    print(f"   - Total features: {sum(len(p) for t in consolidated['tasks'].values() for p in t['phases'].values())}")
    
    return output_path

if __name__ == "__main__":
    merge_validation_configs()