#!/usr/bin/env python3
"""
Quick script to check parquet file structure without dependencies
Uses only built-in modules to inspect file metadata
"""

import os
import sys
import struct
import json

def read_parquet_footer(filepath):
    """Read basic parquet file metadata using only built-ins"""
    with open(filepath, 'rb') as f:
        # Parquet files end with PAR1
        f.seek(-4, 2)
        magic = f.read(4)
        if magic != b'PAR1':
            return None, "Not a valid Parquet file (missing PAR1 magic bytes)"
        
        # Footer length is 4 bytes before magic
        f.seek(-8, 2)
        footer_length = struct.unpack('<I', f.read(4))[0]
        
        # Read footer
        f.seek(-(8 + footer_length), 2)
        footer_data = f.read(footer_length)
        
        # Basic info from file size
        file_size = os.path.getsize(filepath)
        
        return {
            'file_size_mb': file_size / (1024 * 1024),
            'footer_size': footer_length,
            'valid_parquet': True
        }, None

def check_datasets():
    """Check all parquet files in the project"""
    workspace = "/mnt/c/Users/jmontp/Documents/workspace/locomotion-data-standardization"
    
    # Find all parquet files
    parquet_files = []
    for root, dirs, files in os.walk(workspace):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.endswith('.parquet'):
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, workspace)
                parquet_files.append((relpath, filepath))
    
    print(f"Found {len(parquet_files)} parquet files:\n")
    
    for relpath, filepath in sorted(parquet_files):
        info, error = read_parquet_footer(filepath)
        if error:
            print(f"✗ {relpath}")
            print(f"  Error: {error}")
        else:
            print(f"✓ {relpath}")
            print(f"  Size: {info['file_size_mb']:.2f} MB")
        print()

def test_python_imports():
    """Test if required packages can be imported"""
    print("Testing Python package availability:\n")
    
    packages = [
        ('pandas', 'Data manipulation'),
        ('numpy', 'Numerical computing'),
        ('plotly', 'Interactive plotting'),
        ('pyarrow', 'Parquet file reading'),
        ('matplotlib', 'Static plotting'),
        ('kaleido', 'PNG export for plotly')
    ]
    
    available = []
    missing = []
    
    for package, description in packages:
        try:
            __import__(package)
            available.append(package)
            print(f"✓ {package:12} - {description}")
        except ImportError:
            missing.append(package)
            print(f"✗ {package:12} - {description}")
    
    print(f"\nSummary: {len(available)}/{len(packages)} packages available")
    
    if missing:
        print(f"\nTo install missing packages, run:")
        print(f"python3 -m pip install --user {' '.join(missing)} --break-system-packages")
    
    return len(missing) == 0

if __name__ == "__main__":
    print("=== Parquet File Structure Check ===\n")
    
    # First test Python imports
    if not test_python_imports():
        print("\n⚠️  Some packages are missing. Data inspection will be limited.\n")
    
    print("\n=== Checking Parquet Files ===\n")
    check_datasets()
    
    # If pandas is available, do more detailed check
    try:
        import pandas as pd
        print("\n=== Detailed Dataset Information ===\n")
        
        # Check a sample file
        sample_files = [
            "source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet",
            "source/conversion_scripts/Umich_2021/umich_2021_phase.parquet"
        ]
        
        workspace = "/mnt/c/Users/jmontp/Documents/workspace/locomotion-data-standardization"
        
        for relpath in sample_files:
            filepath = os.path.join(workspace, relpath)
            if os.path.exists(filepath):
                print(f"Inspecting: {relpath}")
                try:
                    df = pd.read_parquet(filepath)
                    print(f"  Shape: {df.shape}")
                    print(f"  Columns ({len(df.columns)}): {', '.join(df.columns[:10])}...")
                    
                    if 'subject_id' in df.columns:
                        print(f"  Subjects: {df['subject_id'].nunique()}")
                    if 'task_name' in df.columns:
                        print(f"  Tasks: {df['task_name'].unique()[:5].tolist()}...")
                    if 'phase_r' in df.columns or 'phase' in df.columns:
                        phase_col = 'phase_r' if 'phase_r' in df.columns else 'phase'
                        print(f"  Phase range: {df[phase_col].min():.1f} - {df[phase_col].max():.1f}")
                    
                    # Check 150-point compliance
                    if 'subject_id' in df.columns and 'task_name' in df.columns:
                        print("\n  Checking 150-point compliance:")
                        compliant = 0
                        non_compliant = 0
                        
                        for (subj, task), group in df.groupby(['subject_id', 'task_name']):
                            if len(group) % 150 == 0:
                                compliant += 1
                            else:
                                non_compliant += 1
                                if non_compliant <= 3:  # Show first few issues
                                    print(f"    ✗ {subj} - {task}: {len(group)} points")
                        
                        print(f"    Compliant: {compliant}, Non-compliant: {non_compliant}")
                    
                except Exception as e:
                    print(f"  Error reading file: {e}")
                print()
                
    except ImportError:
        print("\n(Install pandas for detailed dataset inspection)")
    
    print("\nDone!")